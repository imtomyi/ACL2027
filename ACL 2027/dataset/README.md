# Dataset workspace

Use this folder for the study corpora and their privacy-reviewed derivatives. The folder name or location does not make data anonymous; privacy status depends on the documented transformations and re-identification risk.

## Current five-corpus collection

Use [`corpora/`](corpora/README.md) as the single browsing entry point for the
five obtained datasets:

| Corpus | Acquisition | Working-data status |
|---|---|---|
| DREDDIT | Complete | Restricted derivative exists; governance gates still apply |
| AGYW/community-men focus groups | Complete | Restricted derivative exists; governance gates still apply |
| KODIS | Complete | Private exploratory human–human turn bundle validated; unsplit and not manuscript sampling eligible |
| CaSiNo | Complete | Raw snapshot only; preprocessing not started |
| AMI scenario meetings | Complete | Selective raw snapshot only; preprocessing not started |

The entries in `corpora/` link to the established on-disk locations so existing
loaders continue to work and sensitive data are not duplicated.

## Shared folder layout

| Folder | Purpose | Default handling |
|---|---|---|
| `raw/` | Untouched source downloads or exports | Restricted; never publish or edit in place |
| `deidentified/` | Working copies after documented identifier removal or replacement | Restricted unless separately cleared; verbatim online text may remain searchable |
| `release/` | Only artifacts approved for public release | Add only after ethics, license, terms, and privacy review |

Data files are ignored by default. The tracked README files preserve the structure without exposing study data.

The obtained five-corpus collection is DREDDIT, the AGYW/community-men focus
groups, KODIS, CaSiNo, and AMI scenario meetings. Technical validation or public
availability alone does not clear any corpus for real experiments. Project-wide
authorization and review gates are documented in
[`../governance/README.md`](../governance/README.md).

- **Dreaddit and AGYW**: the existing restricted bundles and their fail-closed sampling, quarantine, freeze, and two-reviewer workflow are documented in [PROCESSING.md](PROCESSING.md) and [DREADDIT_AGYW_READINESS.md](DREADDIT_AGYW_READINESS.md). Their real records remain ineligible pending the documented governance and privacy-review gates.
- **KODIS**: the received workbook, aggregate audit, and standalone private exploratory parser are documented in [KODIS_EXPLORATORY.md](KODIS_EXPLORATORY.md). The parser retains 2,076 nonempty human–human dialogues in one unsplit exploratory lane and excludes human–AI rows and all nontranscript workbook fields except outcome and source-row lineage. This does not clear KODIS for a manuscript experiment.
- **CaSiNo**: acquisition status, source integrity, privacy boundary, and the participant-linkage split blocker are documented in [casino/README.md](casino/README.md).
- **AMI scenario meetings**: selective acquisition, source integrity, excluded modalities, and connected-component split requirements are documented in [ami_meetings/README.md](ami_meetings/README.md).
- **CANDOR**: retained as a synthetic fixture and legacy adapter documentation only; no real CANDOR corpus is present.
- **Shared record contract**: [schemas/README.md](schemas/README.md) defines the compatible record shape for future processed records.

## KODIS, CaSiNo, and AMI acquisition details

Their exact source artifacts are present, but none currently has a frozen
manuscript experiment role:

- **[KODIS](KODIS_EXPLORATORY.md)**: the received workbook is hash-bound and its human–human dialogue text has a private, validated exploratory conversion. The workbook does not expose stable cross-dialogue participant linkage, so all converted records remain in `exploratory_unsplit`.
- **[CaSiNo](casino/README.md)**: the official CC BY 4.0 repository snapshot is pinned to commit `2f6ed4a6a55110152a7699fbaa8150d6036314be`. The public JSON does not expose a stable cross-dialogue participant token, so its supplied random split is rejected for WarrantRoute and no project split has been assigned.
- **[AMI scenario meetings](ami_meetings/README.md)**: the official CC BY 4.0 manual-annotation archive is preserved, with only scenario-meeting transcript, segment, and restricted speaker-linkage resources selectively extracted. No audio, video, slides, signals, questionnaires, or participant-demographic files were extracted. It is a candidate alternative to CANDOR for multi-party dialogue.

CaSiNo and AMI use `raw/upstream/` for the immutable downloaded artifact,
`raw/extracted/` for the checksum-verified restricted source snapshot,
`manifests/` for text-free provenance and aggregate inventories, and an
intentionally empty `processed/` directory. KODIS remains under `raw/kodis/`,
with its restricted exploratory output under
`deidentified/kodis_exploratory_private/`.

Source manifests and adapter templates are in `manifests/`. Generated records remain under `deidentified/` and are restricted even after validation.

All fictional fixtures, demo outputs (including `kodis_demo`), synthetic
qualification packets, and their naming/handling rules are indexed in
[SYNTHETIC_DATA.md](SYNTHETIC_DATA.md). Start there when reproducing or extending
synthetic-only work.

## Record before analysis

For each dataset, document:

1. dataset name, version, source, collection or download date, and file hash;
2. population, domains, language, sample-selection rule, and split construction;
3. license, platform terms, consent or secondary-use permission, and the IRB or ethics determination reference;
4. fields retained and removed, identifier substitutions, free-text review, quotation handling, and residual re-identification risks;
5. access controls, approved model or vendor processing, retention and deletion schedule, and withdrawal or deletion procedure where applicable; and
6. the exact files and fields cleared for release.

Use **de-identified** when direct identifiers have been removed or replaced but a person might still be found through searchable text, metadata, a linkage key, or contextual clues. Use **anonymized** only when the team has documented that individuals are no longer reasonably identifiable and the transformation cannot be reversed.
