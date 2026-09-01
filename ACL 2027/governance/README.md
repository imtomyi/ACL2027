# WarrantRoute project-wide governance readiness

Status: **personal-local-only processing is active for the existing Dreaddit and
CaCHe/AGYW working copies**. Formal, human-facing, cloud, publication, and
redistribution workflows remain blocked.

The active personal lane is a single-user, private exploratory workflow. It
permits only the pinned deidentified Dreaddit and AGYW records, a model served
at the numeric loopback address `127.0.0.1`, and restricted outputs under
`Storage/`. It does not assert institutional or external approval and does not
permit cloud/API processing, human-rater exposure, publication, submission,
quotation, redistribution, or release.

The ten-gate evidence system below is retained only for a future formal or
publication workflow. It is not applicable to the personal-local lane and the
personal readiness report therefore returns zero required external gates.

The checker reads governance JSON only. It never discovers or opens corpus files, processed records, prompts, ratings, or source-derived text.

## Personal-local readiness

The restricted local record uses `gate_mode: personal_local_only`. In this
mode, `personal_local_scope_eligible` records only whether the declared corpus
is in scope. This metadata-only report does not inspect live inputs and is not
sufficient by itself to start execution. The older `real_text_ready` signal
deliberately remains false so that personal use cannot unlock human-review or
publication tooling.

```bash
python3 governance/scripts/check_project_readiness.py \
  --record governance/local/project_governance.local.json \
  --as-of <CURRENT-UTC-TIMESTAMP> \
  --output governance/local/readiness_report.local.json
```

The exact corpus, hash, compute, storage, and output-label restrictions are
defined by `policies/personal_local_diagnostic_v1.json`. Validate the policy and
both pinned working copies before a personal experiment starts:

```bash
python3 governance/scripts/check_personal_local_policy.py \
  --policy governance/policies/personal_local_diagnostic_v1.json
```

## Formal/publication ten-gate framework

Each corpus must complete the same ten gates, in this exact order:

1. `institutional_determination`
2. `source_platform_authorization`
3. `provider_model_processing`
4. `exact_corpus_input_contract`
5. `two_person_excerpt_privacy_review`
6. `cluster_aware_sampling`
7. `frozen_study_manifest`
8. `rater_and_service_access_controls`
9. `retention_deletion_controls`
10. `release_controls`

Completion is corpus-, version-, endpoint-, role-, and purpose-specific. Evidence does not transfer automatically between corpora, model products, raters, or releases. Model approval does not authorize rater display; rater-display approval does not authorize quotation or release.

An approved gate needs a nonempty evidence reference, approval authority identifier, evidence version, approval timestamp, expiry timestamp, and last version-verification timestamp. The checker independently rejects expired, future-effective, or version-unverified approvals. `pending`, `rejected`, `expired`, missing, or malformed means blocked.

## Formal evidence records

Start with the tracked templates:

- `templates/project_governance.template.json` — governed corpus lanes, ten gates each, endpoint profiles, and current declared input state;
- `templates/reviewer_registry.template.json` — pseudonymous reviewer identities only;
- `templates/privacy_review_log.template.json` — text-free excerpt/context hashes, decisions, use permissions, and at least two distinct reviewer IDs per excerpt.

Completed records belong in `governance/local/`, which is ignored and must be mode `0700`; files must be mode `0600`. The checker refuses a non-template record elsewhere.

The governance record must not contain source text, participant identities, raw source identifiers, credentials, provider keys, browser account details, reviewer names/emails, or signature images. Use references to institutionally approved evidence stores. Privacy-review packet and excerpt IDs must be project pseudonyms (`PKT_…` and `EXC_…`), owner IDs must use `OWNER_…`, and none may encode source or personal identifiers. Pseudonymized records are not anonymous and must never be described as anonymous. The readiness report itself exposes only controlled corpus/status/role labels, counts, hashes, booleans, and blocking reason codes.

## Formal gate-specific minimums

- Institutional: project-specific determination version covering secondary use, protected-text model processing, human rater exposure, and release review.
- Source/platform: exact source/version and terms versions, with separate affirmative scope for restricted preparation, model processing, rater display, quotation, and release review.
- Model/provider: provider, tenant/account reference, product or endpoint, region, exact model and snapshot, API and terms versions, data classification, training disabled, retention/deletion, human-access or abuse-monitoring conditions, subprocessors, and approval expiry.
- Input contract: received version, restricted source receipt and SHA-256, split, experimental role, allowed/prohibited fields, and purpose.
- Privacy review: packet-manifest SHA-256 and a text-free record showing two distinct current `REV_...` reviewers for every excerpt and displayed context.
- Sampling: versioned plan and hash, exact corpus cluster units, and complete-cluster preservation: Dreaddit posts; AGYW focus groups plus transcript-local speakers; KODIS dialogue-participant connected components; and CANDOR conversation-speaker connected components.
- Freeze: versioned frozen study manifest and SHA-256.
- Rater/service: protocol, consent, withdrawal, approved roles, least privilege, encryption, and access logging.
- Retention/deletion: versioned schedule, future project/provider deletion deadlines, procedure, verification, incident response, and owner.
- Release: versioned release manifest and hash, exact permitted artifact classes, completed privacy review, and license/attribution review. Processing clearance never implies release clearance.

## Run the formal deterministic check

Tracked blocked baseline:

```bash
python3 governance/scripts/check_project_readiness.py \
  --record governance/templates/project_governance.template.json \
  --reviewer-registry governance/templates/reviewer_registry.template.json \
  --privacy-log governance/templates/privacy_review_log.template.json \
  --as-of 2026-08-25T00:00:00Z
```

The tracked result is `reports/synthetic_only_readiness.json`: all four real lanes are `false` and every corpus is 0/10 gates. Its synthetic lane is a software-test status only; it never authorizes manuscript evidence, model selection, results, tables, or figures. Regenerate a local current report with an explicit UTC `--as-of`; do not silently reuse an old readiness result.

Run `python3 governance/scripts/check_manuscript_data_policy.py` separately
before every manuscript build or export. The readiness checker intentionally
does not inspect publication artifacts.

Run `python3 governance/scripts/check_required_manuscript_citations.py` before
the same builds and exports. This separate check ensures that the six required
thematic-analysis and adjacent clinical-evaluation publications remain cited
in active manuscript source; comments, inactive files, and `\nocite` do not
count.

Run `./build_manuscript_pdf.sh` from the workspace root for every local
manuscript build. It runs both manuscript checks and writes the sole compiled
manuscript PDF to
`output/pdf/warrant-route-acl2027-current-manuscript.pdf`. A rendered manuscript
PDF in `overleaf/`, `overleaf/exports/`, or `tmp/` is a policy violation.

## Formal evidence is not current approval

The request-package references are official pages to review as of 2026-08-25. They are not approvals and do not establish that archived data, API access, model processing, rater display, or release is allowed. In particular:

- Dreaddit remains blocked pending institutional review and Reddit confirmation through the currently authorized research route; do not assume the legacy archive is exempt.
- The AGYW Figshare deposit and CC BY 4.0 license do not replace this project's secondary-use, model-processing, rater, privacy, or release determination.
- A real KODIS workbook is present for restricted private exploration, but no
  authorized governed input has been declared and none of the ten gates is
  completed. The real CANDOR distribution is absent. Access forms, upstream
  IRB/consent statements, receipt, or a successful download do not complete the
  gates.

See `requests/` for PI, IRB, data-provider, model-provider, and rater evidence checklists. No request is submitted by these files.
