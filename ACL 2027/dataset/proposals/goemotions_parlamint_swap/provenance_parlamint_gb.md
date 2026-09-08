# Record before analysis: ParlaMint-GB

Status: **DRAFT stub. Incomplete. Not a clearance to process.**
Date started: 2026-08-29 (America/Chicago)

Follows the six-point record-before-analysis contract in `dataset/README.md`.
Fields marked TODO must be completed from the actual download before any
processing. Verified fields are marked VERIFIED with their basis.

## 1. Identity, source, date, hash

- Dataset name: ParlaMint-GB (British Parliament component of ParlaMint).
- Version: ParlaMint 3.0, CLARIN.SI handle `11356/1486`, archive
  `ParlaMint-GB.tgz`. VERIFIED from the downloaded source archive. The archive
  expands under `ParlaMint-GB.TEI/`.
- Source: ParlaMint project, CLARIN ERIC. Reference paper: Erjavec et al., The
  ParlaMint corpora of parliamentary proceedings, Language Resources and
  Evaluation, 2023. VERIFIED (citation and repository).
- Download date: 2026-09-01 (Asia/Seoul).
- File hashes: downloaded archive
  `dataset/raw/parlamint_gb/ParlaMint-GB.tgz` SHA-256
  `ec1f6d82976904866c710123b5d77d6aad20886c44240236e3d442c0708c018a`.
  Gzip integrity check passed, and the archive lists 6,677 tar members. Record
  checksums for extracted files only after a processing pipeline selects them.

## 2. Population, domains, language, sampling, splits

- Population: members of the British Parliament and other on-the-record speakers
  in House of Commons and House of Lords proceedings.
- Domain and language: recorded as categorical fields in Table 1. Not restated
  here.
- Document unit: one debate or agenda item, with speaker turns retained for
  context. Fix at freeze. TODO to finalize the unit and counts.
- Selection rule and split role: all of ParlaMint-GB is reserved for held-out
  cross-domain descriptive evaluation. No development or tuning use. The CaChe
  comparison remains the sole confirmatory held-out test in the frozen
  four-corpus design.
- Clustering: resample over debate-level source clusters for the bootstrap. Fix
  the exact cluster key at freeze.

## 3. License, terms, consent, ethics

- License: Creative Commons Attribution 4.0 International (CC BY 4.0), uniform
  across the ParlaMint 3.0 corpora. VERIFIED (CLARIN.SI repository). Permits
  redistribution and commercial use with attribution.
- Platform and secondary use: parliamentary proceedings are public records.
  Record the attribution string required by the license. TODO.
- Consent: not applicable in the individual-consent sense. Speakers contribute to
  the public record.
- Ethics determination: record this project's determination reference for model
  processing and rater exposure. TODO. Public availability and a permissive
  license do not by themselves satisfy this gate.

## 4. Fields retained and removed, identifiers, re-identification risk

- Retained for analysis: speech and segment text, debate or agenda structure, and
  a document key for clustering. TODO to confirm exact fields.
- Removed from analysis: precise timing, raw internal identifiers, and any
  metadata not needed for packet construction. TODO to enumerate.
- Identifiers: speaker names are part of the public record. Record whether
  speaker names are retained, replaced, or excluded from model and router
  features. TODO.
- Residual risk: low relative to the other study corpora, since speakers are
  public officials on the record. Still record the handling decision.

## 5. Access, approved processing, retention, deletion

- Access controls: stored under `dataset/raw/parlamint_gb/` with restricted
  handling until release review. Directory permissions are `0700`; archive
  permissions are `0600`.
- Approved model or vendor processing: none documented yet for execution. Local
  open-weight reviewer and candidate-generation models named in the
  preregistration still require the project governance determination and
  activation freeze before use. Record any external inference endpoint and its
  terms before use.
- Retention and deletion: follow the workspace retention schedule. TODO to record
  the schedule reference.

## 6. Files and fields cleared for release

- Cleared for release: none yet. CC BY 4.0 permits redistribution with
  attribution, and the specific derived files cleared for release are decided
  after analysis and review. TODO.
