# Two-corpus processing protocol

The current study uses only **Dreaddit** and the **CaCHe AGYW/community-men focus groups**. No third corpus is selected or implied here.

## Experimental roles

| Corpus partition | Role | What remains frozen before access |
|---|---|---|
| Dreaddit official train | Development and pilot data | Not applicable |
| Dreaddit official test | In-domain audit | Packet rules, prompts, and duplicate-removal rules |
| All 11 AGYW/community-men FGDs | Held-out cross-domain evaluation | Prompts, model snapshot, packet rules, defect definitions, routing features, thresholds, expert-minute budget, outcomes, and analysis code |

AGYW is **held out from WarrantRoute development**, not “unopened,” “model-unseen,” or guaranteed absent from model training. The public deposit predates this study and has already been used in published LLM research.

## Build and validate

From the workspace root:

```bash
python3 dataset/scripts/prepare_corpora.py
python3 dataset/scripts/validate_corpora.py
```

The builder verifies upstream checksums before processing. Generated records and provenance maps are written under `dataset/deidentified/`, which is ignored by version control and restricted to the local user. Despite that directory name, the records are not anonymous: exact or lightly masked natural-language text can remain identifiable through content and context.

## Dreaddit decisions

- The author archive contains 2,838 train rows and 715 test rows (3,553 labeled segments from 2,929 posts).
- Original post IDs, timestamps, engagement metadata, and the unused LIWC/DAL features are excluded from analysis records. Project-specific post and record IDs replace the released IDs.
- Obvious URLs, email addresses, Reddit user mentions, and handles are masked, but every excerpt still requires manual privacy review.
- The official splits share no post ID, but three exact texts occur in both splits under different post IDs and conflicting labels. The matching training rows are retained for audit but made ineligible for sampling. Later within-train exact duplicates are likewise ineligible. This leaves 2,817 eligible development rows and all 715 audit rows.
- Stress labels and subreddit are sampling/audit variables; they are not thematic ground truth and are not exposed as router features. The released `confidence` field is excluded because 98 test rows have a value of zero, which is incompatible with the paper's stated majority-agreement definition and retained-item rule.
- The active personal-local policy permits the pinned restricted working copy to
  be processed by the loopback-only local model for a single-user diagnostic.
  It still forbids human-rater display, cloud/API processing, publication,
  quotation, and redistribution. The separate formal/publication lane remains
  blocked until its documentary requirements are completed.

## AGYW decisions

- The source is the 11-file UIC Figshare deposit, version 1, DOI `10.25417/uic.26495884.v1`, licensed CC BY 4.0. Every local transcript matches the upstream MD5.
- Source papers report 107 participants (54 AGYW and 53 community men), written consent, participant-number labels, and ethics review/favorable opinion. This does not replace the present project's secondary-use, rater-exposure, or model-processing determination.
- The refined parser uses a fixed 11-file allowlist and explicit per-file translation formats. It records stable FGD/turn IDs, transcript-local speaker IDs, source line spans, source hashes, translation status, moderator context, and prior-turn references.
- It preserves 3,575 participant turns and 369 collective turns. The legacy three-word rule identifies 3,076 primary-eligible turns but no longer deletes the 499 short participant turns; short and collective turns remain available as interaction context.
- Normalized transcript-local speaker labels yield 106 observed participant keys, one fewer than the 107 participants reported in the paper. Participant coverage must not be claimed until this mismatch is reconciled.
- A February-dated filename conflicts with the paper's reported June 2022--January 2023 period, and another filename conflicts with its transcript header. Dates and locations are therefore excluded from model/router features.
- Treat the transcripts as public, participant-numbered, and selectively redacted—not anonymized. Every excerpt shown to raters or considered for release requires two-person privacy and permissions review.

## Comparable evaluation sampling

Do not call an arbitrary half of Dreaddit's test set “representative.” Determine the number of base packets from the power analysis and expert-time budget, then sample the same preregistered number from the Dreaddit in-domain audit and AGYW cross-domain evaluation. Preserve source clusters: group Dreaddit segments by post and AGYW turns by FGD and transcript-local speaker. Match packet construction and context/token limits, and report corpus-specific results rather than treating individual turns as independent observations.
