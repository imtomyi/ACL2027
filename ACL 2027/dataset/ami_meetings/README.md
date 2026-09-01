# AMI scenario-meeting source package

This directory contains a restricted, source-only acquisition of the official AMI manual annotation archive for the scenario-meeting subset. Acquisition, integrity checks, safe selective extraction, and aggregate inventory are complete. No experimental records, labels, samples, or splits have been produced.

## Official source and license

- Download page: <https://groups.inf.ed.ac.uk/ami/download/>
- Artifact: <https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip>
- Preserved filename: `ami_public_manual_1.6.2.zip`
- Size: 22,887,865 bytes
- SHA-256: `b56e5babb2496b8795deeeda7e71178d7fbc9963f94276cf2a3f4b56ebbc9f9d`
- License: Creative Commons Attribution 4.0 International (`CC BY 4.0`), verified from the embedded `LICENCE.txt`

There is an upstream version-label inconsistency: the official URL and filename say `1.6.2`, while the embedded README says “release 1.7” and is dated 16 June 2014. The server reports a last-modified date of 10 April 2017. This package is therefore identified by the exact URL, filename, byte length, and checksum; it does not assume that the two release labels are equivalent.

## Layout

- `raw/upstream/`: immutable exact upstream ZIP, mode `0600`
- `raw/extracted/ami_public_manual_1.6.2_scenario/`: safely selected scenario resources, directories `0700` and files `0600`
- `manifests/`: source receipt, aggregate manifest, and per-file checksum inventory
- `processed/`: intentionally empty; no preprocessing has started

The AMI-local `.gitignore` excludes `raw/`, `processed/`, and the detailed
per-file inventory. This README and the aggregate receipt/manifest may be
version-controlled; the detailed inventory remains restricted because hashes
of enumerable archive paths are not a privacy boundary.

## Selective extraction

The extracted source subset contains 1,108 files (84,481,539 bytes):

- 552 orthographic word XML files: four channels for each of 138 scenario meetings
- 552 speech-segment XML files: four channels for each scenario meeting
- `corpusResources/meetings.xml`, retained only as a restricted source mapping for meeting/channel/global-speaker lineage
- the upstream README, license, and annotation manifest

The 138 meetings comprise 35 meeting series: 60 `ES`, 38 `IS`, and 40 `TS`. Source meeting-to-speaker mappings contain 140 distinct global speaker identifiers and form 35 connected components. Any future experimental split must use these connected components as indivisible groups so a linked speaker cannot cross splits.

Aggregate XML inspection found 793,764 orthographic word elements and 69,258 segment elements. These are source counts, not experiment counts or claims of usable examples.

No transcript text is copied into the documentation or aggregate manifests.
The restricted per-file inventory records one-way hashes of source paths,
sizes, roles, and content checksums; it does not copy raw source paths or
participant identifiers. It must remain untracked because source-path hashes
could be matched against the finite upstream archive namespace.

## Deliberate exclusions

No audio, video, slides, signals, or other media were acquired or extracted. Questionnaires, participant demographics, `corpusResources/participants.xml`, and all non-transcript manual annotation categories were not extracted.

The exact official annotations ZIP does contain `corpusResources/participants.xml` and other annotation categories. Preserving the exact upstream artifact was required, so those members remain inside the restricted immutable ZIP; they were not selected for extraction or inspected for data content.

The selected XML still contains source identifiers, transcript text, timing attributes, and extra meeting metadata. It is restricted source material and is not anonymous. Future preprocessing must emit only pseudonymous identifiers, preserve conversation/speaker/turn lineage, remove precise timestamps and raw source identifiers, and retain only explicitly approved transcript fields. Outputs must be described as pseudonymized, never anonymous.

## Validation completed

- ZIP size and SHA-256 match the acquired official artifact and observed HTTP content length.
- ZIP integrity passed; no unsafe paths, duplicate/case-colliding paths, encrypted members, symlinks, or non-regular members were found.
- Every selected file was streamed through an allowlist into a new restricted directory and matches its ZIP member by SHA-256.
- All 1,105 selected XML files parse successfully.
- Every scenario meeting has word and segment resources for channels A–D.
- All raw directories are `0700`; all raw files are `0600`.

## Still required before experiments

No AMI data is currently sampling-eligible. Before any experiment can use it, the project still needs an AMI-specific transcript adapter, an approved pseudonymization secret, field-level minimization and redaction checks, manual privacy review, dialogue/order/completeness validation, and a split manifest built from the 35 meeting–global-speaker connected components. The source archive and extracted files must remain unchanged.

See `manifests/ami_manual_annotations_v1.6.2_receipt.json` for provenance and integrity details and `manifests/ami_scenario_source_manifest.json` for aggregate source and readiness status.
