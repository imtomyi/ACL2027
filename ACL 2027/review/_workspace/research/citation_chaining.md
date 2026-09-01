# Citation-chaining audit

Search cutoff: 2026-08-24. Seeds checked: 15. Reviewer: one.

## Forward checks by seed

| Seed | OpenAlex pass 1 / pass 2 | Stable set? | Semantic Scholar retrieved | Google Scholar diagnostic |
|---|---:|:---:|---:|---:|
| `dai_2023_llm_in_loop` | 80 / 80 | yes | 171 | not available |
| `parfenova_2024_proposal` | 7 / 7 | yes | 9 | not available |
| `parfenova_2025_inductive_coding` | 10 / 10 | yes | 17 | not available |
| `hicode_2025` | 0 / 0 | yes | not available | not available |
| `quallm_2025` | 3 / 3 | yes | not available | not available |
| `thematic_lm_2025` | 12 / 12 | yes | 46 | not available |
| `lloom_2024` | 39 / 39 | yes | 139 | not available |
| `details_2025` | 6 / 6 | yes | 11 | not available |
| `chen_2026_open_code_metrics` | 0 / 0 | yes | not available | not available |
| `yu_2025_same_company` | 0 / 0 | yes | not available | not available |
| `tama_2026` | 1 / 1 | yes | 14 | not available |
| `auto_ta_2025` | 0 / 0 | yes | 10 | not available |
| `sft_ta_2025` | 0 / 0 | yes | 3 | not available |
| `position_clinical_ta_2025` | 0 / 0 | yes | 2 | not available |
| `yi_2026_provenance_refinement` | 0 / 0 | yes | 0 | not available |

## Backward-chain outcomes

| Candidate | Parent seed | Full-text outcome | Eligibility outcome |
|---|---|---|---|
| Further Explorations on the Use of Large Language Models for Thematic Analysis: Open-Ended Prompts, Better Terminologies and Thematic Maps | `tama_2026` | retrieved and inspected | include_core |
| Investigation of the Inter-Rater Reliability between Large Language Models and Human Raters in Qualitative Analysis | `matveyenko_2026_muse` | retrieved and inspected | include_core |
| laato 2025 gioia cot | `matveyenko_2026_muse` | sought but not reproducibly retrieved | awaiting_full_text |

Two candidates were reproducibly retrieved, inspected in full, and retained as core evidence (2 total): De Paoli (2024) and Borse et al. (2025). Laato et al. (2025) remains explicitly sought but not retrieved and was not added to the master evidence table.

## Screening state

The API/sample union contains 397 deduplicated records; 23 exactly match a current master DOI/title and 177 new records passed the deliberately broad title-keyword triage.

The generated JSON is the audit source of truth. It preserves per-seed parentage, source-specific failures, the complete OpenAlex first-pass records, Semantic Scholar records, confirmation differences, and Google Scholar samples.

All 59 focused-scope forward records received a conservative title-level routing decision (exclude_at_title=7, existing_master_version_family=1, seek_full_text_adjacent_or_contextual=14, seek_full_text_potential_core=37). These are retrieval decisions, not full-text inclusion decisions; no forward record was promoted to the master evidence table without complete full-text inspection.

## Interpretation limit

No citation-index saturation claim is made. A stable OpenAlex confirmation pass shows only that this source returned the same records during this run. Google Scholar was not bulk-exportable, Semantic Scholar has index-specific omissions, and Scopus/Web of Science were not available.
