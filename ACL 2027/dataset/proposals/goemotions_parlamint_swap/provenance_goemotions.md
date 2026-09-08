# Record before analysis: GoEmotions

Status: **Record complete for the simplified split. Processing still requires the
project governance determination and a frozen preregistration.**
Download authorized by the user in session on 2026-08-29.
Download date: 2026-08-29 (America/Chicago).
Current local retrieval verified against the recorded hashes: 2026-09-01
(Asia/Seoul).

Follows the six-point record-before-analysis contract in `dataset/README.md`.

## 1. Identity, source, date, hash

- Dataset name: GoEmotions.
- Source: Demszky, Movshovitz-Attias, Ko, Cowen, Nemade, Ravi, GoEmotions, ACL
  2020. Google Research release.
- Retrieval: simplified split, labels, and license from
  `raw.githubusercontent.com/google-research/google-research/master/goemotions/`;
  full-dataset CSVs from
  `storage.googleapis.com/gresearch/goemotions/data/full_dataset/`.
- Local store: `dataset/raw/goemotions/upstream/` (restricted; ignored by git).
- SHA-256:
  - `train.tsv` `1c254a142be5c00e80d819b9ae1bbd36d94b2eeb8f4b1271846508d57e57d9c5`
  - `dev.tsv` `575489c079c9de1097062a01738f998590d6b7ead66dd1c9fd1d2ba01fd8bc62`
  - `test.tsv` `0587b2dd8b27b97352adbfc3fb083d46005c8946657fdc2b1ca8b1cc7f1f8be4`
  - `emotions.txt` `45c3ef86782d2a4d7fedcd6d8c111aa0d0e94720689bd164fac94fefb4495a89`
  - `ekman_mapping.json` `d6b1fea382917c1685c42e1324a0344106be9390f52a3850ce032656d103a328`
  - `sentiment_mapping.json` `801f6f028082141bd38541a4b14d65b33bdc55d29c7b2aaa029fefecf206f76b`
  - `LICENSE` `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
  - `full_dataset/goemotions_1.csv` `cac049036bad5d68d1081f72b65f2cc51e4df82af05e3e22cfa747051cac1af3`
  - `full_dataset/goemotions_2.csv` `f699ecc5aa425c1720c1d02475f1e41815244b680bd75b282eb770d2c76cd84d`
  - `full_dataset/goemotions_3.csv` `467f1e7191af00f2e76cc7f425885c2dc304bea8aff284b10e8c460d22f2e1af`

## 2. Population, domains, language, sampling, splits

- Population: authors of public Reddit comments sampled by the release
  maintainers. No recruitment by this project.
- Language and domain: recorded in Table 1. Not restated here.
- Splits (simplified): `train` 43,410 comments, `dev` 5,426, `test` 5,427.
  Comment identifiers are unique within each split, and the splits are pairwise
  disjoint (train and test share 0 ids, dev and test share 0 ids).
- Study roles: `train` supports development, `test` is the in-domain audit,
  `dev` has no manuscript role. The Table 1 candidate pool is `train` + `test`.
- Document unit: one labeled comment. No post or thread grouping exists in the
  simplified split, so the bootstrap cluster is the comment.

## 3. License, terms, consent, ethics

- License: Apache-2.0 (the retrieved repository `LICENSE`), with the dataset
  content documented as CC BY 4.0 in the TensorFlow Datasets catalog. Permits
  redistribution and commercial use with attribution.
- Platform terms: content originates from Reddit. Record whether the permissive
  release license is treated as sufficient for this project's model processing.
  TODO determination.
- Consent: no individual consent for public Reddit comments. The release relies
  on public availability and, for the simplified split, on omitting identifiers.
- Ethics determination: project determination reference for secondary analysis
  and model processing. TODO. A permissive license does not satisfy this gate.

## 4. Fields retained and removed, identifiers, re-identification risk

- Full-dataset CSV columns (verified in `goemotions_1.csv`): `text, id, author,
  subreddit, link_id, parent_id, created_utc, rater_id, example_very_unclear`,
  and 28 emotion columns.
- The full release is NOT de-identified: `author` holds real Reddit usernames
  (observed sample `Brdd9`), with `subreddit`, `created_utc`, and thread ids.
  This combination is directly re-identifying.
- Simplified split fields: `text`, emotion-id list, and comment `id` only. No
  author, subreddit, timestamp, or thread ids.
- Decision: analysis uses the simplified split. The full-dataset identifier
  fields are excluded from analysis and never reach model or router features.
- Residual risk: verbatim comment text may remain searchable even without the
  identifier fields. Treat as de-identified, not anonymized.
- Correction logged: an earlier manuscript sentence stating the maintainers
  "removed direct author identifiers" was inaccurate for the full release and
  has been rewritten to describe the simplified-split decision.

## 5. Access, approved processing, retention, deletion

- Access controls: `dataset/raw/goemotions/upstream/`, restricted, git-ignored.
- Approved processing: local open-weight reviewer and candidate-generation models
  named in the preregistration. Record any external inference endpoint and terms
  before use. TODO.
- Retention and deletion: follow the workspace retention schedule. TODO to record
  the schedule reference.

## 6. Files and fields cleared for release

- Cleared for release: none yet. The license permits redistribution, but the
  specific derived files cleared for release are decided after analysis and
  privacy review. TODO.

## 7. Verified corpus statistics (deterministic, whitespace word count)

| Split | Comments | Words | Avg words |
|---|---|---|---|
| train (development) | 43,410 | 557,594 | 13 |
| test (in-domain audit) | 5,427 | 69,087 | 13 |
| dev (unused) | 5,426 | 69,424 | 13 |
| **Candidate pool (train+test)** | **48,837** | **626,681** | **13** |

Table 1 GoEmotions row is populated from the candidate-pool figures above. These
are verified corpus-preparation counts, not experimental results. Labels: 28
(27 emotions plus neutral).
