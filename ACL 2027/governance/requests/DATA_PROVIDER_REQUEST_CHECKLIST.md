# Source and data-provider request checklist — drafts only

Status: **evidence to review as of 2026-08-25; no request submitted, no terms accepted, and no authorization claimed**. Official pages can change. A link, license statement, form, upstream IRB statement, download, or prior archive does not itself complete the project’s institutional, platform, model, rater, retention, privacy, or release gates.

Do not enter browser-account details, credentials, names, emails, postal addresses, signatures, or agreement attestations into tracked files. Complete required identifying fields only in the provider’s official channel after PI/institutional approval, then retain a non-sensitive evidence reference and version in the restricted local governance record.

## Common request controls

- [ ] PI verifies the exact noncommercial academic purpose, data minimum, users, locations, model endpoints, raters, outputs, retention, and deletion plan.
- [ ] Institution confirms the request and each proposed use are in scope.
- [ ] Provider/platform confirms exact source/version, users, model processing, rater display, quotation, release, retention, and deletion permissions.
- [ ] Project records the terms/version reviewed, approval authority/reference, effective date, expiry/re-review date, and last verification date.
- [ ] Project does not infer permission for one use from permission for another.
- [ ] Provider-facing statements are rechecked for truth immediately before submission.

## Dreaddit / Reddit

### Current official evidence to review

- [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms): effective 2023-06-19; last revised 2026-07-20.
- [Reddit Developer Terms](https://redditinc.com/policies/developer-terms): effective 2024-09-24; last revised 2026-03-24.
- [Developer Platform & Accessing Reddit Data](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data), updated 2026-05-28: states that Reddit for Researchers (RFR) is the authorized avenue for research and that research through developer APIs or unauthorized third-party tools violates policy.
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), updated 2026-06-05: states that research using Reddit data collected outside RFR violates policy.
- [Reddit for Researchers Program](https://support.reddithelp.com/hc/en-us/articles/49381918834964-Reddit-for-Researchers-Program), updated 2026-06-02.

These current statements are not retroactive-scope conclusions or project authorization. Treat Dreaddit as blocked pending Reddit confirmation/RFR handling; do not assume a legacy archive exception.

The PI/institution must review the current permitted-use, privacy/retention, and AI-use restrictions in both terms documents against the exact WarrantRoute design; the dates and links above do not record acceptance or approval.

### RFR eligibility and application evidence

- Accredited-university PI/researcher and official institutional email.
- Detailed proposal identifying the specific subreddits and data needed.
- IRB/comparable ethics approval or exemption attachment.
- Institutional sponsor email, such as faculty adviser, chair, or research-office official.
- Prior research links, where available, to support the application.
- Live form fields observed: email; subject/details; Reddit account name; educational institution; institution country; research purpose; estimated timeline/current status; noncommercial-academic acknowledgment; attachments.

Each source-data user must apply separately. Do not share credentials.

### Program constraints to capture in the project record

- No reidentification.
- Keep only minimal/offline copies when necessary.
- Permanently delete project data after the project, except any minimal records the program permits.
- Use deletion-aware publication practices.
- No redistribution or credential sharing.
- Send the preprint to Reddit as required.
- Access is limited to at most one year unless separately renewed.

### Questions that require an affirmative Reddit answer

- [ ] Is any use of the existing Dreaddit copy allowed, or must source data be reacquired/used only through RFR?
- [ ] Are the exact proposed derived fields, pseudonymization, model endpoints, contextual rater display, quotation, aggregate outputs, and release artifacts permitted?
- [ ] What subreddit/data specification, deletion propagation, preprint, audit, and one-year access conditions apply?
- [ ] Must every project member/rater separately apply, and are external model/rater services prohibited or separately reviewable?

## AGYW/community-men focus groups

### Current official evidence to review

- [Cache2 Focus Group Discussion Transcripts: AGYW and Community Males](https://indigo.uic.edu/articles/dataset/Cache2_Focus_Group_Discussion_Transcripts_AGYW_and_Community_Males/26495884), DOI `10.25417/uic.26495884`, is presented on Figshare under CC BY 4.0.

The deposit and license do not establish this project’s human-subjects/secondary-use determination or authorize every model, rater, quotation, or release use.

### Project-specific confirmations

- [ ] Institution confirms the exact sensitive-text secondary use and safeguards.
- [ ] Source/license version, attribution form, permitted transformations, quotation rules, and any participant-consent limitations are verified.
- [ ] Exact model processing and human-rater context are approved separately.
- [ ] Focus-group and transcript-local-speaker clusters remain intact across splits.
- [ ] Retention/deletion, privacy review, and permitted release artifacts are recorded.

## KODIS / USC ICT

### Current official evidence to review

- [KODIS ACL Anthology paper](https://aclanthology.org/2025.naacl-long.637/) (Hale et al., 2025) links the access pathway and describes the source research context. Paper statements about source IRB/consent are context, not approval for this project.

### Live request fields observed

- Primary researcher name.
- University-affiliated email.
- Date.
- Institution.
- Address.
- Short intended-use description.
- Affirmative EULA agreement.

Leave identity, signature, and agreement fields for the user/institution; this repository must not complete or submit them.

### Terms shown with the request

- Noncommercial research only.
- No redistribution of the dataset or parts of it to third parties.
- Illustrative publication use is allowed only when subject identity is protected.
- Cite Hale et al. (2025).
- USC ICT may change the EULA and require re-signing.
- No warranty.

### Requested scope draft

> **PI verification required; not submitted.** Request only complete human-human KODIS dialogues for WarrantRoute’s noncommercial academic evidence-routing and qualitative-audit study. Exclude surveys, demographics, and human-AI dialogue. Retain only the minimum dialogue text and pseudonymous conversation/speaker/turn lineage; do not train models, reidentify or contact participants, redistribute data, or use it commercially. Any model processing, rater display, illustrative excerpt, retention, and deletion will follow the exact EULA and institutional determination.

- [ ] Confirm whether external model endpoints or rater services count as prohibited third-party disclosure.
- [ ] Confirm the permitted excerpt/illustration scope, identity-protection standard, and required citation.
- [ ] Record the EULA version and re-signing trigger; recheck before every use after a terms change.

## CANDOR / BetterUp

### Current official evidence to review

- [BetterUp CANDOR research page and request route](https://www.betterup.com/research/candor-research).

### Live request fields observed

- First name and surname.
- Organizational/institutional email; the form states generic email is not approved.
- Research institution/organization.
- Data flavor.
- Specific research-use description.
- TalkBank-access choice.
- Explicit terms agreement.

Leave identity, signature, and agreement fields for the user/institution; this repository must not complete or submit them.

### Requested selection and retention scope

- Select only **`No Video Media (~10GB)`** for this project.
- Select **TalkBank `No`** for the preferred original BetterUp route unless TalkBank use is separately intended and approved.
- After authorized receipt, retain only the original per-conversation Cliffhanger transcript CSV fields needed for conversation/speaker/turn lineage. Prefer `transcript_cliffhanger.csv` if the authorized package contains it.
- Exclude audio, video, surveys, demographics, precise timestamps, raw source identifiers, and unrelated metadata.
- The filename, package layout, fields, and receipt version remain unverified assumptions until authorized download; do not invent a receipt or result.

### Terms shown with the request

- Legitimate academic/scientific noncommercial research only.
- No republication of the original or derivative dataset without BetterUp permission.
- Do not identify, locate, or gather information about participants.
- If personally identifying information is self-disclosed, do not use, analyze, share, or publish it.
- Download links are valid for seven days.

### Requested-use draft

> **PI verification required; not submitted.** Request CANDOR `No Video Media (~10GB)` for WarrantRoute’s noncommercial academic evidence-routing and qualitative-audit study. Following authorized receipt, retain only the minimum original Cliffhanger transcript CSV text and pseudonymous conversation/speaker/turn lineage. Exclude media, surveys, demographics, timestamps, and raw source identifiers. Do not train models, reidentify or contact participants, redistribute the original or derivative dataset, or use it commercially. Keep linked speakers/conversations together across splits, and require two-person contextual privacy review before any model/rater display or proposed quotation.

- [ ] Confirm that the exact transcript-only fields, pseudonymization, model endpoint, rater display, and retention/deletion plan are permitted.
- [ ] Obtain separate written permission before any original/derivative dataset republication; do not treat experimental output clearance as dataset republication permission.
- [ ] Plan authorized receipt within the seven-day link window and immediately verify checksum/version in restricted storage.
- [ ] Escalate any self-disclosed PII for exclusion; do not use, analyze, share, or publish it.

## Completion rule

A submitted/accepted request still leaves every other governance gate independent. Real data remain blocked until the exact ten-gate checker passes for that corpus at the intended execution time.
