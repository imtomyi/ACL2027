# Dataset Background and Experimental Inputs

This English record explains what data were used, how they became reviewer inputs, and which interpretations the files support. It is an internal provenance document, not manuscript-ready evidence. See [the packet viewer](index.html) for every observed packet and [the generated inventory](VERIFIED_INVENTORY.md) for verified counts.

## The Four Different Objects

| Object | What it actually is |
|---|---|
| Original corpus | Reddit text, focus-group transcripts or parliamentary proceedings obtained from an existing source. The corpus names were not invented by this experiment. |
| Evidence packet | A locally constructed group of four excerpts, a research question, metadata and a claim. PKT IDs, working-bank names and n100 subset names are local experiment identifiers. |
| Claim and intended flaw | A locally constructed interpretation and target flaw category. In the current n100 sets the claim generator is recorded as a deterministic working-packet builder, despite the field name `llm_generated_qualitative_claim`. |
| Reviewer/quality output | A model's review of that packet, or a separate judge's assessment of the review. Neither is an original corpus annotation. |

The initial `draftpkt_20260901T052834Z` experiment differs: its recorded claim-generator field names Qwen3 8B. The viewer preserves the actual field per packet. Do not generalize the current deterministic construction to every historical packet.

## Current n100 Selection

The authoritative binding is [the prompt-identity repair configuration](../../experiments/rq2_role_prompted_llm/config/table3_n100_prompt_identity_repair_v1.json). Each dataset contributes 100 packets, with 20 target constructions in each of five intended flaw categories. There are 400 packets and 1,600 displayed excerpt occurrences overall. The three reviewer models and methods reuse these same source packets.

The subset selector sorts truth records by packet ID, groups them by intended flaw, takes 20 per group and sorts the selected IDs. Thus n100 means 100 selected packets per dataset, not 100 repetitions of a sample, not 100 people and not the original dataset's official size. Selection of this subset is deterministic. Earlier source selection can use a different rule, including the seeded ParlaMint draw.

The five intended flaw categories are `unsupported_evidence`, `source_concentration`, `counterevidence_loss`, `contextual_flattening` and `unsupported_abstraction`. These targets come from local construction logic. The truth-map files explicitly do not establish independent human adjudication that every intended flaw is present. Original stress or emotion labels are not substitutes for flaw ground truth.

## Dreaddit

**Origin:** Turcan and McKeown (2019), *Dreaddit: A Reddit Dataset for Stress Analysis in Social Media*. Its original purpose is stress identification in social-media text. [Source paper](https://aclanthology.org/D19-6213/).

**Actual experimental input:** Eligible `development_train` records derived from `dataset/raw/dreaddit/dreaddit-train.csv`, via `dataset/deidentified/dreaddit/records.jsonl`. The working builder sorts records, uses distinct post source IDs, groups four excerpts per packet and supplies a deterministic claim. The main subset comes from `dreaddit_dev580_working_v1`, not the earlier 25- or 100-packet bank. The official test split is not used in the main n100 set.

**Original location:** Each catalog entry links to a CSV data-row number and the stored sentence range through the analysis record's provenance. The displayed excerpt is prepared text with applicable identifier masking, not a promise of unmodified raw text. The model saw the segment, not the complete post or thread. Sentence-range provenance in the catalog is additional traceability information and was not in the historical packet's local_context.

**Theoretical relevance:** Stress narratives can motivate studying whether qualitative interpretations preserve the evidence and local situation. This is an interpretation of possible methodological relevance, not a finding of the current experiment. The data and scores do not establish clinical validity or diagnostic accuracy.

[Local source manifest](../../dataset/manifests/dreaddit_source_manifest.json).

## GoEmotions

**Origin:** Demszky et al. (2020), *GoEmotions: A Dataset of Fine-Grained Emotions*. The original annotations distinguish 27 emotions and neutral in Reddit comments. The official name is GoEmotions; `GoEmotion` in some table artifacts is an alias. [Source paper](https://aclanthology.org/2020.acl-main.372/).

**Actual experimental input:** The simplified official `train.tsv`, not the full-dataset CSVs. The builder retains comments with at least five words, normalizes whitespace and groups eligible records in source-row order. The working bank contains 9,540 prepared packets; its balanced subset contributes 100 to the main experiment. Prepared bank capacity must not be reported as the number evaluated.

**Original location:** `source_record_id` encodes the one-based TSV row. The catalog verifies the normalized text against that exact row and records its original emotion IDs. The simplified input contains no surrounding thread text. Four comments in one packet must not be described as an actual conversation or one author's narrative.

**Theoretical relevance:** The comments provide a setting for testing grounded interpretation of short, affective utterances. This is a proposed connection to the study question. Original emotion annotations do not certify the injected claim's defect, review quality or a model's ability to repair documents.

[Local provenance](../../dataset/proposals/goemotions_parlamint_swap/provenance_goemotions.md).

## CaChe

**Origin:** The local manifest identifies Mehta (2024), *Cache2 Focus Group Discussion Transcripts AGYW and Community Males*, version 1, DOI `10.25417/uic.26495884.v1`. The source concerns adolescent girls and young women and community men, with discussion of the pandemic, relationships and health in rural western Kenya. CaChe is this project's display name; `agyw_focus_groups` is its internal corpus ID. [Source deposit](https://indigo.uic.edu/articles/dataset/Cache2_Focus_Group_Discussion_Transcripts_AGYW_and_Community_Males/26495884).

**Actual experimental input:** Eligible participant turns in the deidentified records file, using English source passages or English translations. The bank interleaves source FGDs before grouping four records. Main n100 contains 400 distinct turns from all 11 transcript files, not 400 participants. The working bank has 765 prepared packets.

**Original location:** Each turn maps to a named transcript file, line interval, turn index and speaker label. Some packets include a moderator question and preceding-record IDs. Preceding IDs alone are not additional visible transcript text. A packet can combine different focus groups, so its four excerpts are not necessarily a continuous exchange.

**Theoretical relevance:** This source has a direct connection to qualitative interpretation and the importance of speaker and moderator context. That makes context-preserving review a plausible research question, but does not establish that the generated claims are valid thematic analyses or that their intended flaws were independently verified.

**Handling:** Public and selectively redacted is not equivalent to anonymous. The source manifest documents filename/date discrepancies and remaining permissions/privacy requirements. The historical held-out split label is preserved as metadata; these already-used records are not newly untouched evaluation data. The source page could not be refreshed during this build, so these details are attributed to the local manifest rather than a new web verification.

[Local source manifest](../../dataset/manifests/agyw_source_manifest.json).

## ParlaMint-GB

**Origin:** The local provenance identifies the British component of ParlaMint 3.0, CLARIN.SI handle `11356/1486`. It consists of public parliamentary speech, including the Commons and Lords. [Source repository](https://hdl.handle.net/11356/1486). The repository could not be refreshed during this build; version details are grounded in the locally recorded archive provenance.

**Actual experimental input:** `dataset/raw/parlamint_gb/ParlaMint-GB.tgz`. The full-sample builder parses TEI speaker turns, joins segment text, normalizes whitespace and retains turns of 8 to 800 words. The recorded eligible pool has 607,907 turns. A seeded draw (`20260901`) selects 400 turns, then sorts them by year, chamber, session and record before grouping into 100 packets. These 100 packets are the entire `parlamint_gb_fullsample_eval100_working_v1` bank.

**Original location:** The main set's 400 distinct turn records come from 352 session source IDs. The catalog verifies exact text and speaker matches in the original archive and records the archive member, XML utterance identifier and ordinal. The archive is read without extraction. Any non-unique source match is explicitly recorded as such.

**Theoretical relevance:** Institutional discourse provides a different setting for testing whether a review respects evidence, context and policy disagreement. This is a rationale for studying transfer across domains, not evidence that the current diagnostic experiment establishes such transfer. A packet can mix unrelated debates. Sorting the source draw before assigning consecutive flaw groups can associate the flaw group with time or chamber; that design choice should not be hidden.

[Local provenance](../../dataset/proposals/goemotions_parlamint_swap/provenance_parlamint_gb.md).

## What the Models Actually Received

The current detection outputs are the prompt-identity-repaired records, with 3,600 role/model records across four datasets. Generalist uses the generalist review. Fixed role uses `qualitative_methods` consistently. All roles combines the three stored roles: `generalist`, `qualitative_methods` and `domain`. It is not a fourth separately generated source dataset. Historical WarrantRoute replay uses the same source packet family; its routing policy is a separate object.

The catalog reconstructs full historical reviewer prompts with the repository's `build_historical_prompt` function and verifies them against every current output's recorded hash. That function removes only `known_intended_flaw_type`, `known_intended_flaw_note` and `review_instruction`. It retains nested `theme_name`, `explanation` and `boundary_conditions` in the claim object. Those fields can reveal the intended flaw. Prompt identity across models does not make this a blind test without answer hints.

The separate Credibility/Conformability quality judge receives a sanitized source context, reviewed claim and review bundle, with excerpt/source IDs remapped. Its source excerpts and claim are checked against all 400 packets across its 3,600 units. Generation explanations are not part of that sanitized payload. This judge evaluates reviews, not the original corpus labels. The catalog links one exact stored unit per packet and indexes every other unit by file and line. Schema-repair attempts are not new source samples.

## Limits on Interpretation

- Real source text and synthetic or deterministic claim construction are different provenance layers. Do not describe the whole packet as a naturally occurring flawed document.
- Intended flaw balance is an experimental construction, not the natural frequency of these flaws in the source population.
- A stored output with `status=valid` passes the software schema criterion. It is not a correctness label or scientific-quality guarantee.
- An integrity check verifies identity and traceability. It does not establish representative sampling, independence, human gold labels, blinded evaluation or publication eligibility.
- The current workspace policy keeps these working diagnostic records under `Storage/`. This catalog does not change that policy or move any result into a manuscript.
- Reusing source records across methods is useful for paired comparison, but does not create new independent observations. Earlier bank variants and repaired output copies are explicitly separated in the inventory.

For precise counts, use the generated inventory rather than the original corpus size or a bank name. For the exact words a model could inspect, use the packet and historical prompt rather than a paraphrase of the dataset's subject.
