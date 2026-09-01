# CaSiNo corpus snapshot

This directory holds a provenance-pinned, raw-only snapshot of the official
[kushalchawla/CaSiNo](https://github.com/kushalchawla/CaSiNo) repository. It
was collected from the official GitHub archive route at commit
`2f6ed4a6a55110152a7699fbaa8150d6036314be` on 2026-08-26 UTC. The upstream
repository describes CaSiNo as 1,030 two-party campsite-negotiation dialogues
and licenses the repository under Creative Commons Attribution 4.0
International (CC BY 4.0).

This is an acquisition checkpoint, not an experiment-ready corpus. No CaSiNo
record has been transformed, sampled, approved for research use, or written to
an experimental split by this work. `processed/` is intentionally empty.

## Local layout

- `raw/upstream/` contains the untouched GitHub-generated archive.
- `raw/extracted/` contains its byte-content extraction at the pinned commit.
- `manifests/casino_acquisition_receipt.json` binds the source URL, commit,
  archive checksum, license, and handling state.
- `manifests/casino_source_file_manifest.json` binds every extracted file by
  byte length and SHA-256.
- `manifests/casino_schema_profile.json` reports structural counts and
  integrity checks without reproducing dialogue text, source identifiers, or
  demographic values.

Raw directories are mode `0700`; raw files are mode `0600`. A CaSiNo-local
`.gitignore` excludes raw and processed artifacts from version control while
allowing only this README and non-content manifests to be tracked.

## Content and privacy boundary

The exact upstream snapshot necessarily contains human-participant dialogue as
well as participant information in the same JSON records: demographics,
personality measures, preferences, free-text reasons, and negotiation outcomes.
Those fields remain restricted raw source material. They have **not** been
ingested into a working output. The corpus must not be described as anonymous;
public availability and categorical speaker-role labels do not establish
anonymity or eliminate possible self-disclosure in dialogue text.

Before any later preprocessing, the project must separately document its
research-use authority, ethics/privacy determination, license attribution plan,
manual privacy review, and an approved field allowlist. Demographics,
personality/survey measures, free-text participant reasons, and outcome surveys
must remain excluded unless a later, explicit protocol authorizes them. No such
authorization is claimed here.

## Verified source structure

Aggregate-only inspection of `data/casino.json` found:

- 1,030 unique dialogue rows and 2,060 participant records;
- 14,297 `chat_logs` entries: 11,919 ordinary message entries containing
  228,675 whitespace-delimited words, plus 2,378 structured negotiation events;
- 396 dialogues with 4,615 strategy-annotation records; and
- the supplied random split contains 900 train, 30 validation, and 100 test
  dialogues, with no dialogue-ID overlap and complete coverage of the full
  file.

The upstream documentation reports 11.6 utterances per dialogue. The inspected
ordinary-message count gives 11.5718 per dialogue; the larger 13.8806 average
over all `chat_logs` entries includes structured negotiation events.

Three annotated dialogues contain one more ordinary message than annotation
record. All 4,615 annotation text members occur somewhere in their associated
dialogue, but positional equality is therefore not universal. This is recorded
as an upstream alignment caveat and was not repaired or silently normalized.

## Split and participant-linkage blocker

The public JSON supplies two dialogue-local speaker-role tokens but no stable
cross-dialogue participant token. The repeated role labels must not be treated
as participant identities. Linkage must not be reconstructed from demographics,
personality measures, preferences, free-text reasons, dialogue content, or any
other sensitive profile.

Consequently, the upstream random train/validation/test split is rejected for
WarrantRoute: its dialogue-ID disjointness does not demonstrate participant
isolation. CaSiNo remains unassigned to any project split. The blocker can be
resolved only by trustworthy provider-supplied participant linkage that can be
used privately for component-aware splitting, or by assigning the entire corpus
to one unsplit experimental role after all governance and privacy gates are
satisfied. Neither resolution has occurred here.

## Version and license caveats

The acquisition is a repository snapshot at an exact commit, not a claimed
formal release tag. The upstream split README calls the included split random
but does not record a seed or generation procedure. GitHub did not provide a
publisher-signed checksum; the SHA-256 values here are local integrity bindings
to the exact bytes collected. Consult the bundled `LICENSE` and the
[official repository](https://github.com/kushalchawla/CaSiNo) for attribution
requirements; this README is not legal or ethics approval.
