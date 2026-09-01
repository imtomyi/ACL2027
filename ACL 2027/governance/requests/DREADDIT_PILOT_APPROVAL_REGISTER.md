# Dreaddit pilot approval register

Status: **submission-ready project drafts; external decisions pending**.

## Prepared project-controlled evidence

| Gate | Prepared artifact | Current status |
|---|---|---|
| Exact corpus input contract | `DREADDIT_PILOT_INPUT_CONTRACT.md` | Drafted; approval reference pending |
| Cluster-aware sampling | `DREADDIT_PILOT_SAMPLING_PLAN.md` | Drafted; seed and approval pending |
| Data flow and safeguards | `DREADDIT_PILOT_DATA_FLOW.md` | Drafted for review |
| Sample-size basis | Direction J planning recommendation and CSV | Complete as a pre-pilot feasibility analysis |
| Source integrity | Dreaddit source manifest and checked audits | Structurally validated; not use authorization |

## Decisions or evidence that must come from outside this drafting step

| Gate | Required next action | Evidence to record after approval |
|---|---|---|
| Institutional determination | PI submits the IRB/institutional request with the input contract, sampling plan, data flow, rater plan, and endpoint profiles | Determination reference/version, scope, authority, dates |
| Source/platform authorization | Confirm current Reddit/source permission for restricted preparation, model processing, rater display, quotation, and release separately | Terms/authorization versions, scope, authority, dates |
| Provider model processing | Select exact approved endpoint(s) and document training, retention, deletion, human access, region, and subprocessors | `MEP_…` profile IDs and approval dates |
| Two-person privacy review | Nominate and authorize at least two reviewers, then create the seed-bound candidate bundle after prerequisite gates pass | Registry, packet-manifest hash, completed text-free ledger |
| Frozen study manifest | Freeze packet rules, prompts, models, outcome definitions, exclusions, assignments, and analysis hashes | Manifest reference/version/hash and freeze time |
| Rater/service controls | Approve roles, consent, compensation, withdrawal, least privilege, encryption, logging, and any platform | Protocol/consent/access versions and evidence dates |
| Retention/deletion | Approve deadlines, backup behavior, incident response, owner, and deletion verification | Schedule/procedure versions, owner ID, dates |
| Release controls | Approve exact artifact classes; default to aggregate non-text outputs only | Release manifest/hash, privacy and attribution decisions |

## Required order

1. PI fact-check and scope approval.
2. Institutional and source/platform determinations.
3. Exact model endpoint and rater-service approvals.
4. Finalize retention, deletion, incident response, and release class.
5. Activate two privacy reviewers in the restricted registry.
6. Freeze the selection control and sampling seed commitment.
7. Select 72 candidate post clusters and complete two-person review.
8. Validate all gates mechanically before any model call or rater display.

No row in the local governance JSON should change to `approved` until its
underlying versioned evidence exists and the readiness checker accepts it.
