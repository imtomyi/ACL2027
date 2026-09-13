# Table 3-Style Results Review

Snapshot: 2026-09-10. Private diagnostic report, not a manuscript result table.
Original experiments, frozen files and the historical Table 3 are unchanged.

This report contains three separate panels. Their protocols, judges, sample sizes and exposure histories differ. Do not rank methods across panels or treat the new online version as already tested.

## A. Most Recent Executed ACE Experiment

Run: `ace_flaw_gemma_expansion_dev10_eval80_20260910`. Intentionally paused on 2026-09-10 at 10:06 KST.
Model and judge: local Gemma 3 4B. Development: 120/120 exposures. Evaluation: 515/640 arm reviews (80.5%). Both quality dimensions are binary for 194/640 planned reviews.
Each corpus has 80 planned evaluation packets, with a seed-control E0 and an adapted E3 review per packet. Completed reviews are not unique packets across checkpoints.

**Read percentages with their denominators.** A quality cell is `resolved-case percentage (true/binary N; U=unresolved among completed reviews)`. All resolved values here happen to be true. This is not 100% success over all packets. Unresolved cases and pending work must not be hidden.

| **Dataset** | **Method** | **Model** | **Completed / planned** | **TP/N** | **Recall (%)** | **Credibility (%)** | **Conformability (%)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dreaddit | ACE-inspired WarrantRoute-Lite (E0) | Gemma 3 4B | 65/80 | N/A | N/A | 100.0 (24/24; U=41) | 100.0 (60/60; U=5) |
| Dreaddit | ACE-inspired WarrantRoute-Lite (E3) | Gemma 3 4B | 65/80 | N/A | N/A | 100.0 (25/25; U=40) | 100.0 (60/60; U=5) |
| GoEmotions | ACE-inspired WarrantRoute-Lite (E0) | Gemma 3 4B | 65/80 | N/A | N/A | 100.0 (9/9; U=56) | 100.0 (64/64; U=1) |
| GoEmotions | ACE-inspired WarrantRoute-Lite (E3) | Gemma 3 4B | 64/80 | N/A | N/A | 100.0 (9/9; U=55) | 100.0 (62/62; U=2) |
| CaChe | ACE-inspired WarrantRoute-Lite (E0) | Gemma 3 4B | 64/80 | N/A | N/A | 100.0 (26/26; U=38) | 100.0 (59/59; U=5) |
| CaChe | ACE-inspired WarrantRoute-Lite (E3) | Gemma 3 4B | 64/80 | N/A | N/A | 100.0 (26/26; U=38) | 100.0 (59/59; U=5) |
| ParlaMint-GB | ACE-inspired WarrantRoute-Lite (E0) | Gemma 3 4B | 64/80 | N/A | N/A | 100.0 (38/38; U=26) | 100.0 (48/48; U=16) |
| ParlaMint-GB | ACE-inspired WarrantRoute-Lite (E3) | Gemma 3 4B | 64/80 | N/A | N/A | 100.0 (37/37; U=27) | 100.0 (46/46; U=18) |

`E0` is the seed-only control; `E3` is the checkpoint after three development epochs. These are checkpoints, not the Generalist / Fixed role / All roles methods.
`TP/N` and `Recall` are deliberately unavailable in this panel: an incomplete, same-model provisional reference inventory is not an independently validated flaw answer key. No zero or historical TP value has been substituted.
All 515 recorded final decisions are `no_flaw_established`, with zero recorded grounded matches. Review-quality passes therefore must not be interpreted as successful flaw detection or verified repair.

### E3 Coverage and Pending Work

Binary coverage below uses the full planned denominator of 80. False and technical-quality counts are zero in these rows; unresolved and pending counts are distinct.

| **Dataset** | **Credibility true / false / unresolved** | **Credibility binary coverage** | **Conformability true / false / unresolved** | **Conformability binary coverage** | **Pending reviews** |
| --- | --- | --- | --- | --- | --- |
| Dreaddit | 25 / 0 / 40 | 31.3% (25/80) | 60 / 0 / 5 | 75.0% (60/80) | 15 |
| GoEmotions | 9 / 0 / 55 | 11.3% (9/80) | 62 / 0 / 2 | 77.5% (62/80) | 16 |
| CaChe | 26 / 0 / 38 | 32.5% (26/80) | 59 / 0 / 5 | 73.8% (59/80) | 16 |
| ParlaMint-GB | 37 / 0 / 27 | 46.3% (37/80) | 46 / 0 / 18 | 57.5% (46/80) | 16 |

### Matched E3 Minus E0

Only the same packet with a binary judgment in both checkpoints contributes to a paired change. Zero observed paired change is not evidence of statistical equivalence.

| **Dataset** | **Credibility change (pp)** | **Credibility paired N** | **Conformability change (pp)** | **Conformability paired N** |
| --- | --- | --- | --- | --- |
| Dreaddit | 0.0 | 24 | 0.0 | 60 |
| GoEmotions | 0.0 | 9 | 0.0 | 62 |
| CaChe | 0.0 | 26 | 0.0 | 59 |
| ParlaMint-GB | 0.0 | 37 | 0.0 | 46 |

### Playbook Result

| **Dataset** | **Development exposures** | **Seed rules** | **Learned rules at E3** | **Proposed edits** | **Accepted additions** | **Accepted refinements** | **Distinct learned rules retrieved** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dreaddit | 30 | 2 | 0 | 9 | 0 | 0 | 0 |
| GoEmotions | 30 | 2 | 0 | 32 | 0 | 0 | 0 |
| CaChe | 30 | 2 | 0 | 21 | 0 | 0 | 0 |
| ParlaMint-GB | 30 | 2 | 0 | 24 | 0 | 0 | 0 |

The executed Playbooks remained seed-only. The newly implemented online update path has not produced these results and must not be credited with improvements or blamed for this run's outcomes.
CaChe remains the previously authorized within-source diagnostic.

Sources: [Quality CSV](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910/dataset_quality.csv>); [Paired changes CSV](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910/paired_changes.csv>); [Playbook CSV](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910/playbook_result.csv>); [Pause record](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910/pause_record.json>).

## B. Historical n100 Table 3

These are the 48 existing recorded rows, reproduced without changing any number. They are historical working diagnostics, not a newly matched comparison with Panel A.
WarrantRoute here is `n100_same_model_table3_20260905_v2` / `live_evidence_revision_loop_same_model_v1`, not the latest online Playbook version.
Credibility and Conformability are historical Qwen-judged review/projection pass rates. The retained Recall confidence intervals also differ by historical method. The original source notes remain authoritative; this report does not revalidate their methodology.

| **Dataset** | **Method** | **Model** | **TP/N** | **Recall (%)** | **Credibility (%)** | **Conformability (%)** |
| --- | --- | --- | --- | --- | --- | --- |
| Dreaddit | Generalist | Qwen3 8B | 67/100 | 67.0 [57.3, 75.4] | 90 | 85 |
| Dreaddit | Generalist | Llama 3.1 8B | 16/100 | 16.0 [10.1, 24.4] | 72 | 71 |
| Dreaddit | Generalist | Gemma 3 4B | 73/100 | 73.0 [63.6, 80.7] | 90 | 88 |
| Dreaddit | Fixed role | Qwen3 8B | 76/100 | 76.0 [66.8, 83.3] | 85 | 80 |
| Dreaddit | Fixed role | Llama 3.1 8B | 24/100 | 24.0 [16.7, 33.2] | 75 | 72 |
| Dreaddit | Fixed role | Gemma 3 4B | 83/100 | 83.0 [74.5, 89.1] | 91 | 88 |
| Dreaddit | All roles | Qwen3 8B | 77/100 | 77.0 [67.8, 84.2] | 96 | 92 |
| Dreaddit | All roles | Llama 3.1 8B | 52/100 | 52.0 [42.3, 61.5] | 89 | 75 |
| Dreaddit | All roles | Gemma 3 4B | 89/100 | 89.0 [81.4, 93.7] | 95 | 91 |
| Dreaddit | WarrantRoute | Qwen3 8B | 99/100 | 99.0 [97.0, 100.0] | 79.0 | 79.0 |
| Dreaddit | WarrantRoute | Llama 3.1 8B | 68/100 | 68.0 [59.0, 77.0] | 51.0 | 50.0 |
| Dreaddit | WarrantRoute | Gemma 3 4B | 42/100 | 42.0 [33.0, 52.0] | 84.0 | 84.0 |
| GoEmotion | Generalist | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] | 53 | 49 |
| GoEmotion | Generalist | Llama 3.1 8B | 59/100 | 59.0 [49.2, 68.1] | 52 | 46 |
| GoEmotion | Generalist | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] | 67 | 58 |
| GoEmotion | Fixed role | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] | 55 | 50 |
| GoEmotion | Fixed role | Llama 3.1 8B | 37/100 | 37.0 [28.2, 46.8] | 60 | 58 |
| GoEmotion | Fixed role | Gemma 3 4B | 79/100 | 79.0 [70.0, 85.8] | 72 | 64 |
| GoEmotion | All roles | Qwen3 8B | 91/100 | 91.0 [83.8, 95.2] | 70 | 53 |
| GoEmotion | All roles | Llama 3.1 8B | 77/100 | 77.0 [67.8, 84.2] | 59 | 48 |
| GoEmotion | All roles | Gemma 3 4B | 80/100 | 80.0 [71.1, 86.7] | 79 | 60 |
| GoEmotion | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [100.0, 100.0] | 30.0 | 29.0 |
| GoEmotion | WarrantRoute | Llama 3.1 8B | 63/100 | 63.0 [53.0, 72.0] | 29.0 | 29.0 |
| GoEmotion | WarrantRoute | Gemma 3 4B | 47/100 | 47.0 [37.0, 57.0] | 86.0 | 86.0 |
| CaChe | Generalist | Qwen3 8B | 79/100 | 79.0 [70.0, 85.8] | 97 | 94 |
| CaChe | Generalist | Llama 3.1 8B | 27/100 | 27.0 [19.3, 36.4] | 89 | 87 |
| CaChe | Generalist | Gemma 3 4B | 57/100 | 57.0 [47.2, 66.3] | 98 | 97 |
| CaChe | Fixed role | Qwen3 8B | 76/100 | 76.0 [66.8, 83.3] | 97 | 96 |
| CaChe | Fixed role | Llama 3.1 8B | 30/100 | 30.0 [21.9, 39.6] | 94 | 92 |
| CaChe | Fixed role | Gemma 3 4B | 61/100 | 61.0 [51.2, 70.0] | 98 | 98 |
| CaChe | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] | 100 | 94 |
| CaChe | All roles | Llama 3.1 8B | 55/100 | 55.0 [45.2, 64.4] | 98 | 95 |
| CaChe | All roles | Gemma 3 4B | 71/100 | 71.0 [61.5, 79.0] | 100 | 99 |
| CaChe | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [CI N/A] | 96.0 | 94.0 |
| CaChe | WarrantRoute | Llama 3.1 8B | 64/100 | 64.0 [CI N/A] | 64.0 | 63.0 |
| CaChe | WarrantRoute | Gemma 3 4B | 55/100 | 55.0 [CI N/A] | 97.0 | 97.0 |
| ParlaMint-GB | Generalist | Qwen3 8B | 75/100 | 75.0 [65.7, 82.5] | 94 | 91 |
| ParlaMint-GB | Generalist | Llama 3.1 8B | 24/100 | 24.0 [16.7, 33.2] | 89 | 88 |
| ParlaMint-GB | Generalist | Gemma 3 4B | 48/100 | 48.0 [38.5, 57.7] | 95 | 93 |
| ParlaMint-GB | Fixed role | Qwen3 8B | 67/100 | 67.0 [57.3, 75.4] | 89 | 86 |
| ParlaMint-GB | Fixed role | Llama 3.1 8B | 36/100 | 36.0 [27.3, 45.8] | 90 | 89 |
| ParlaMint-GB | Fixed role | Gemma 3 4B | 67/100 | 67.0 [57.3, 75.4] | 95 | 91 |
| ParlaMint-GB | All roles | Qwen3 8B | 81/100 | 81.0 [72.2, 87.5] | 99 | 89 |
| ParlaMint-GB | All roles | Llama 3.1 8B | 52/100 | 52.0 [42.3, 61.5] | 98 | 90 |
| ParlaMint-GB | All roles | Gemma 3 4B | 69/100 | 69.0 [59.4, 77.2] | 98 | 91 |
| ParlaMint-GB | WarrantRoute | Qwen3 8B | 100/100 | 100.0 [100.0, 100.0] | 79.0 | 72.0 |
| ParlaMint-GB | WarrantRoute | Llama 3.1 8B | 67/100 | 67.0 [57.0, 77.1] | 55.0 | 44.0 |
| ParlaMint-GB | WarrantRoute | Gemma 3 4B | 50/100 | 50.0 [39.8, 60.4] | 87.0 | 84.0 |

`GoEmotion` is retained verbatim from the historical source. The newer panels use `GoEmotions`. No historical label or value was rewritten in its source file.
Sources: [Original Table 3 CSV](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_warrantroute_n100_final.csv>); [Original Table 3 and protocol notes](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/table3_warrantroute_n100_final.md>).

## C. New Online Version: Not Run

Run: `ace_claim_online_v1_dev10_stream80_20260910_prepared`. Status: `prepared_not_started`.
All cells below are placeholders, not measured zeros. Four corpora x 80 stream packets are planned, with one static and one online prediction and one combined quality judgment per arm. The same 10 development packets per corpus are planned for three warm-up epochs. No old result is imported into the new scores.
The new experiment uses Gemma 3 4B only. Qwen and Llama comparisons are not part of this prepared run.

| **Dataset** | **Method** | **Model** | **Completed / planned** | **TP/N** | **Recall (%)** | **Credibility (%)** | **Conformability (%)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dreaddit | Static seed control | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| Dreaddit | ACE-inspired online WarrantRoute | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| GoEmotions | Static seed control | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| GoEmotions | ACE-inspired online WarrantRoute | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| CaChe | Static seed control | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| CaChe | ACE-inspired online WarrantRoute | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| ParlaMint-GB | Static seed control | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |
| ParlaMint-GB | ACE-inspired online WarrantRoute | Gemma 3 4B | 0/80 | N/A | N/A | Not run | Not run |

The initial two seed rules are prepared, but no live online rule learning, C/F judging or performance improvement has been measured. Stored rules, retrieval, reported application and quality changes will be reported separately after an authorized run.
Sources: [Prepared status](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_claim_online_v1_dev10_stream80_20260910_prepared/status.json>); [Prepared CSV](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_claim_online_v1_dev10_stream80_20260910_prepared/results_table_online.csv>); [Online system and experiment design](</Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/experiment_guidelines/ace_claim_online_v1.md>).

## Verification

The eight Panel A rows were independently reconciled to the raw per-item JSON records: processed counts and true/false/unresolved counts for both dimensions match. Raw counts: 120 development results, 515 evaluation results, zero reported technical trajectories, and 194 binary quality pairs.
Panel B is an exact value copy of 48 source CSV rows. This is a transcription check, not a fresh scientific validation of the historical experiment. Panel C is read from the prepared configuration/status and contains no inferred result.

Source CSV SHA-256 digests at report creation:

- historical: `41361059f52edc1beb9b325f7a82746af3c97a1c89d53529af711a0a4537ccb0`
- quality: `81cb624bb5c6249de0c7288e9c9fa7c6891da7f22da7964f616eda683a361e89`
- paired: `99f722e493934ba24d0d47144b8a57dff8e41093b15ef6641faf4a17f624936c`
- playbook: `61b70f767a4b24835586008a2cf0c948ed2d0932b837c9a48f56bb30ff3bc3b6`
