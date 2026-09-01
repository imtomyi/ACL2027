# Dataset plan for WarrantRoute

## Decision

The manuscript documents five candidate corpus lanes:

1. **Dreaddit** is provisionally assigned to development and a secondary in-domain audit.
2. **Cache2 (project alias: CaCHe) AGYW/community-men focus groups** are provisionally assigned to the held-out cross-domain confirmatory evaluation.
3. **KODIS** is the private exploratory dyadic dispute-resolution lane.
4. **CaSiNo** is the source-only dyadic negotiation candidate.
5. **AMI scenario meetings** are the source-only multiparty dialogue candidate.

Only Dreaddit and CaCHe currently have provisional manuscript experimental
roles. KODIS has a validated private exploratory conversion but no manuscript
sampling role. CaSiNo and AMI are acquired, integrity-checked source snapshots;
they have no processed
experimental records, approved model or rater pathway, adopted split, or
sampling eligibility. Their inclusion in a real experiment requires a later
preregistration after corpus-specific validation and governance approval.

“Held out” means that no CaCHe text, generated output, or published theme is
used to choose prompts, packet rules, controlled variants, router features,
thresholds, budgets, stopping rules, or outcomes. It does not mean the public
corpus is model-unseen or absent from model training.

## Source facts and roles

| Corpus | Source and access | Provenance available | Current role |
|---|---|---|---|
| Dreaddit | The author ZIP is publicly downloadable but contains no README or dataset license. The paper reports no ethics determination, Reddit author consent, or privacy procedure. Current use remains conditional on institutional and platform authorization. | Segment ID, post ID, sentence range, subreddit, and exact text; no author ID. | Official train: development. Official test: secondary in-domain audit after packet rules are frozen. |
| Cache2 focus groups (CaCHe) | UIC Figshare version 1, DOI `10.25417/uic.26495884.v1`, CC BY 4.0. Source papers report written consent, participant-number labels, and ethics review/favorable opinion. Current secondary analysis, model processing, and rater exposure still require this project's determination. | Focus group, transcript-local speaker, moderator and peer context, language/translation structure, and source line spans. | All 11 FGDs: held-out cross-domain confirmatory evaluation (provisional assignment). |
| KODIS | Received workbook and provider README. The README specifies collection dates, fields, and citation but no data license or authorization for external model processing or rater disclosure. | Human–human transcript role/order and source-row lineage only in the private output; no raw dyad ID or stable cross-dialogue participant token. | Private `exploratory_unsplit`; not sampling eligible for manuscript results. |
| CaSiNo | Official GitHub repository snapshot pinned to commit `2f6ed4a6a55110152a7699fbaa8150d6036314be`, CC BY 4.0. Public availability does not settle project-specific model, rater, privacy, or release approval. | Dialogue and turn order plus dialogue-local speaker roles. The public JSON has no stable cross-dialogue participant token. | Restricted source-only dialogue candidate; unassigned and not sampling-eligible. |
| AMI scenario meetings | Official manual annotations v1.6.2 archive, CC BY 4.0. Only scenario transcript, segment, and restricted speaker-linkage resources were selectively extracted. | Meeting, channel, segment, word, and global source-speaker linkage in the restricted source. Raw identifiers and precise timing must not reach output. | Restricted source-only dialogue candidate; unassigned and not sampling-eligible. |

## Verified Dreaddit audit

- The public archive contains 3,553 labeled segments from 2,929 posts: 2,838 train rows from 2,343 posts and 715 test rows from 586 posts.
- It covers ten subreddits in five domains. A row is an approximately five-sentence segment, not necessarily a complete post.
- The official splits share no post ID, but three exact texts appear in both partitions under different post IDs and conflicting labels. The refined copy keeps the test instances and makes the matching training rows ineligible.
- The train split also contains 18 later occurrences of within-split exact duplicate text. These are retained for audit but excluded from packet sampling. Duplicate handling leaves 2,817 development rows and 715 audit rows before privacy quarantine. Exact-date cluster quarantine leaves 2,804 development and 712 audit candidate rows, 3,516 rows and 301,279 words in total.
- Original post IDs, timestamps, engagement metadata, the inconsistent `confidence` field, and unused LIWC/DAL features are omitted from analysis records. Project IDs preserve post grouping.
- Because no author identifier exists, Dreaddit cannot support participant counts, participant concentration, participant-disjoint splitting, or claims about distinct people.

## Verified CaCHe AGYW audit

- All 11 local transcripts exactly match the upstream Figshare MD5 values.
- The direct paper reports 107 participants: six AGYW groups with 54 participants and five community-men groups with 53 participants, conducted from June 2022 to January 2023 in English, Swahili, Dholuo, or a mixture and translated into English.
- The refined parser retains 3,575 participant turns and 369 collective turns. The former three-word rule identifies 3,076 primary-eligible turns, but the other turns are preserved for interaction context rather than deleted.
- Stable IDs are scoped to each focus group. Normalization yields 106 observed transcript-local participant keys, one fewer than the 107 participants reported in the paper. Do not claim complete participant coverage until this mismatch is reconciled.
- One filename falls outside the paper's reported collection period and another filename conflicts with its header. Dates and locations are excluded from model and router features.
- The deposit is public, participant-numbered, and selectively redacted. It is not anonymous: sexual and reproductive health narratives, relationships, occupations, places, and other contextual clues may remain identifying.

## Verified KODIS exploratory audit

- The workbook contains 2,860 unique dyads and 107 columns: 2,085 human–human
  and 775 human–AI.
- The private exploratory builder retains 2,076 nonempty human–human dialogues,
  27,121 turns, and 568,333 parsed words; it excludes all human–AI rows and nine
  human–human rows without transcript text.
- Median retained length is 12 messages (IQR 11–14) and 242 words (IQR
  180–334). Nine retained dialogues begin with Seller, and 271 contain at least
  one consecutive same-role transition; the parser preserves both patterns.
- Raw dyad identifiers, timestamps, surveys, demographics, country, points,
  preferences, tactics, and all other workbook fields are excluded from the
  turn bundle.
- The source exposes no stable cross-dialogue participant token. All records
  therefore remain in one `exploratory_unsplit` role, with no participant-level
  or participant-disjoint claim.
- This private conversion is technically fit for local exploratory dialogue
  experiments. It does not establish the permissions, privacy review,
  preregistration, rater pathway, or confirmatory role needed for manuscript
  results.

## Verified CaSiNo source audit

- The pinned source contains 1,030 dialogues, 11,919 ordinary messages, 2,378
  structured negotiation events, and 228,675 whitespace-delimited words in the
  ordinary messages.
- Participant metadata include demographics, personality measures,
  preferences, free-text reasons, and outcomes. These fields, the strategy
  annotations, and structured deal events are excluded from every transcript
  output.
- The paper reports 846 participants, but the public JSON provides no stable
  cross-dialogue participant token. The repeated speaker-role labels are local
  to each dialogue.
- The upstream random 900/30/100 dialogue split is rejected for WarrantRoute
  because dialogue disjointness does not establish participant isolation.
  Linkage must not be reconstructed from profiles or text.
- CaSiNo can advance only if the provider supplies trustworthy private linkage
  or the full corpus is preregistered in one unsplit role after all governance
  and privacy gates are satisfied.

## Verified AMI scenario source audit

- The selected inventory contains 138 four-party scenario meetings in 35
  meeting series, 793,764 orthographic word elements, and 69,258 speech segment
  elements.
- Restricted source mappings contain 140 global speaker identifiers that form
  35 meeting-speaker connected components: 33 components contain four meetings
  and two contain three meetings.
- No audio, video, signals, slides, questionnaires, demographics,
  `participants.xml`, or non-transcript annotation category was extracted.
- The official artifact filename says v1.6.2 while its embedded README says
  release 1.7. The receipt uses the exact URL, filename, size, and checksum and
  does not assume that the labels are equivalent.
- Any future output must remove timing and raw meeting, channel, speaker,
  segment, and word identifiers. All 35 connected components must remain
  indivisible in any project split.

## Sampling and analysis

The pilot-based power analysis and primary serious-error outcomes determine one
preregistered packet count for each assigned evaluation corpus. Human review
time is a secondary implementation measure and comparison control. Do not use an
arbitrary half of Dreaddit's test set or call it “representative.” Apply the
same packet construction and context/token limits to Dreaddit and CaCHe.

Preserve source clusters throughout sampling and uncertainty estimation:

- group Dreaddit segments by post;
- group CaCHe turns by focus group and transcript-local speaker; and
- never treat several turns from one source as independent participants.

Dreaddit stress labels and subreddit categories may support stratified sampling, but are not thematic ground truth. Published CaCHe themes are not used as scoring gold.

KODIS, CaSiNo, and AMI do not enter manuscript generation or sampling while
their roles remain unassigned. If later adopted, KODIS and CaSiNo must each
remain one unsplit role unless
trustworthy participant linkage becomes available, and AMI must be split only
by complete meeting-speaker connected components.

## Privacy and approval gates

1. Obtain the team's institutional determination for every adopted corpus,
   protected-text model processing, and the new rater study.
2. Obtain written confirmation that the specified Dreaddit use is permitted under
   applicable Reddit/platform conditions. If not, do not process the real text
   with an LLM or expose it to raters.
3. Record exactly which CaCHe uses are permitted by the source terms, CC BY
   attribution requirement, institutional determination, and rater consent
   materials.
4. For KODIS, record the allowed private use and approve any model or rater
   access, then freeze its single unsplit exploratory role.
5. For CaSiNo, approve a transcript-only allowlist and resolve the absent
   cross-dialogue participant linkage without profile matching.
6. For AMI, approve transcript-only processing, validate pseudonymization and
   removal of timings/raw IDs, and freeze complete speaker-connected components.
7. Keep raw text, provenance maps, and pseudonymized analysis text restricted.
   Do not describe any corpus or working output as anonymous or anonymized.
8. Require two reviewers to clear every source excerpt shown to raters or
   considered for publication. Mask direct identifiers and minimize dates,
   locations, and contextual detail.
9. Release aggregate results, schemas, code, prompts, and model/run metadata.
   Release source-derived text, ratings, or text-derived
   hashes only with explicit permission, privacy clearance, and a linkage-risk
   review.

## Primary records

1. Dreaddit paper: <https://aclanthology.org/D19-6213/>. Author archive: <https://www.cs.columbia.edu/~eturcan/data/dreaddit.zip>.
2. CaCHe transcript deposit: <https://indigo.uic.edu/articles/dataset/Cache2_Focus_Group_Discussion_Transcripts_AGYW_and_Community_Males/26495884>.
3. Direct CaCHe paper: <https://bmjpublichealth.bmj.com/content/2/2/e001214>.
4. KODIS paper: <https://aclanthology.org/2025.naacl-long.637/>. Local source receipt and exploratory protocol: `dataset/raw/kodis/` and `dataset/KODIS_EXPLORATORY.md`.
5. CaSiNo paper and source: <https://aclanthology.org/2021.naacl-main.254/> and <https://github.com/kushalchawla/CaSiNo>.
6. AMI corpus, download, and ethics documentation: <https://groups.inf.ed.ac.uk/ami/corpus/>, <https://groups.inf.ed.ac.uk/ami/download/>, and <https://groups.inf.ed.ac.uk/ami/corpus/ethicsandconsent.shtml>.
7. Local source receipts: `dataset/casino/manifests/` and `dataset/ami_meetings/manifests/`.
8. Local processing protocol: `dataset/PROCESSING.md`.
