# Final consolidation preview

This is a preview-only consolidation. It does not overwrite `master_evidence.json`, `review_flow.json`, the report, or the workbook.

## Evidence outcome

- Raw source evidence rows: 402.
- Deduplicated retained evidence rows: 237.
- Core records and quality rows: 181 / 181.
- Adjacent/contextual records retained without quality rows: 56.
- Exact DOI/title/version-family duplicate clusters removed at this layer: 165.
- Non-core quality rows intentionally dropped: 9.
- Fatal validation conflicts: 0.

NITA is present once as the 2025-companion journal version of record. The 2026 TA-0336 duplicate was suppressed upstream; input overlap shown by this idempotence rebuild reflects already-published canonical rows re-entering alongside their year companions, not duplicate rows in the canonical master.

## Review-flow outcome

- Database records with terminal title/abstract dispositions: 1360.
- Advanced database records with terminal full-text outcomes: 244; missing outcomes: 0.
- Focused forward-chain candidates mapped: 59; advanced to full text: 54; pending cross-year handoffs: 0.
- Backward-chain candidates resolved: 3.

## Artifacts

- `research/final_consolidation_preview.json`
- `research/final_consolidation_conflict_audit.json`
- `research/final_review_flow_preview.json`

Quality totals remain audit aids and are not study rankings. Fuzzy title/author pairs in the conflict audit are manual-review prompts only and are never automatically deduplicated.
